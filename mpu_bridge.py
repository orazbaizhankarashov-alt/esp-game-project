import time
import socket
from datetime import datetime, timezone

import serial
from serial.tools import list_ports

from firebase_store import save_session, save_event, update_progress

BAUD = 115200
HOST = "127.0.0.1"
PORT = 5005

current_session = None
buffer = ""


# ================= ESP32 =================
def is_valid(line):
    try:
        a, b, c = line.split(",")
        float(a)
        float(b)
        float(c)
        return True
    except:
        return False


def extract_valid_line(raw: str):
    raw = raw.strip()

    if not raw:
        return None

    if raw in ("READY", "MPU_NOT_FOUND", "OTA_READY", "OTA_START", "OTA_END", "WIFI_FAIL"):
        return raw

    if raw.startswith("OTA_ERROR_"):
        return raw

    if is_valid(raw):
        return raw

    return None


def try_open_port(port_name: str):
    try:
        print("Қосылу:", port_name)
        ser = serial.Serial(port_name, BAUD, timeout=1)
        time.sleep(2)

        start = time.time()
        while time.time() - start < 4:
            raw = ser.readline().decode("utf-8", errors="ignore")
            line = extract_valid_line(raw)

            if line is None:
                continue

            print(f"[{port_name}] {line}")

            if line == "READY" or is_valid(line):
                print("ESP32 табылды:", port_name)
                return ser

        ser.close()
        return None

    except Exception as e:
        print("Қате:", port_name, e)
        return None


def connect_esp32():
    while True:
        ports = [p.device for p in list_ports.comports()]
        print("Порттар:", ports)

        for p in ports:
            ser = try_open_port(p)
            if ser is not None:
                return ser

        print("Қайта іздеу...")
        time.sleep(2)


# ================= PROCESSING =================
def start_server():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print("Processing күтілуде...")
    return s


def wait_client(server):
    c, addr = server.accept()
    c.setblocking(False)
    print("Processing қосылды:", addr)
    return c


# ================= FIREBASE =================
def fb_start(pid, game, level):
    global current_session
    current_session = {
        "patient": pid,
        "game": game,
        "start": datetime.now(timezone.utc),
        "score": 0,
        "mistakes": 0,
        "trap": 0,
        "startLevel": level,
        "endLevel": level
    }
    save_event(pid, "start", game)


def fb_update(score=0, mistakes=0, trap=0, level=1):
    if current_session:
        current_session["score"] = score
        current_session["mistakes"] = mistakes
        current_session["trap"] = trap
        current_session["endLevel"] = level


def fb_end(win):
    global current_session
    if not current_session:
        return

    end = datetime.now(timezone.utc)

    save_session(
        "p001",
        current_session["game"],
        current_session["start"],
        end,
        current_session["score"],
        current_session["mistakes"],
        current_session["trap"],
        win,
        current_session["startLevel"],
        current_session["endLevel"]
    )

    duration = int((end - current_session["start"]).total_seconds())
    update_progress("p001", current_session["endLevel"], duration)

    save_event("p001", "end", current_session["game"])

    print("SAVE DONE")
    current_session = None


def handle(line):
    parts = line.split("|")

    if parts[0] != "FB":
        return

    if parts[1] == "START":
        fb_start(parts[2], parts[3], int(parts[4]))

    if parts[1] == "UPDATE":
        data = {}
        for p in parts[2:]:
            if "=" in p:
                k, v = p.split("=")
                data[k] = v

        fb_update(
            int(data.get("score", 0)),
            int(data.get("mistakes", 0)),
            int(data.get("trapHits", 0)),
            int(data.get("level", 1))
        )

    if parts[1] == "END":
        fb_end(parts[2] == "win")


def read_proc(client):
    global buffer
    try:
        d = client.recv(4096)
        if not d:
            return

        buffer += d.decode()

        while "\n" in buffer:
            l, buffer = buffer.split("\n", 1)
            handle(l.strip())

    except BlockingIOError:
        pass
    except:
        pass


# ================= MAIN =================
def main():
    server = start_server()
    client = None
    ser = None

    while True:
        try:
            if client is None:
                client = wait_client(server)

            read_proc(client)

            if ser is None or not ser.is_open:
                ser = connect_esp32()

            raw = ser.readline().decode("utf-8", errors="ignore")
            line = extract_valid_line(raw)

            if line is None:
                continue

            print("ESP32:", line)

            try:
                client.sendall((line + "\n").encode())
            except:
                try:
                    client.close()
                except:
                    pass
                client = None

        except KeyboardInterrupt:
            print("Тоқтатылды")
            break

        except Exception as e:
            print("Қате:", e)

            try:
                if ser and ser.is_open:
                    ser.close()
            except:
                pass

            try:
                if client:
                    client.close()
            except:
                pass

            ser = None
            client = None
            time.sleep(2)

    try:
        if client:
            client.close()
    except:
        pass

    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass

    try:
        server.close()
    except:
        pass


if __name__ == "__main__":
    main()