import time
import socket
import serial
from serial.tools import list_ports

BAUD = 115200
HOST = "127.0.0.1"
PORT = 5005


def is_sensor_line(line: str) -> bool:
    parts = line.split(",")
    if len(parts) != 3:
        return False
    try:
        float(parts[0])
        float(parts[1])
        float(parts[2])
        return True
    except ValueError:
        return False


def is_battery_line(line: str) -> bool:
    parts = line.split(",")
    if len(parts) != 4:
        return False
    if parts[0] != "BATTERY":
        return False
    try:
        float(parts[1])
        float(parts[2])
        float(parts[3])
        return True
    except ValueError:
        return False


def extract_valid_line(raw: str):
    raw = raw.strip()

    if not raw:
        return None

    if is_battery_line(raw):
        return raw

    if raw in ("READY", "MPU_NOT_FOUND", "OTA_READY", "OTA_START", "OTA_END", "WIFI_FAIL"):
        return raw

    if raw.startswith("OTA_ERROR_"):
        return raw

    if is_sensor_line(raw):
        return raw

    return None


def score_port(port_info):
    text = " ".join([
        str(port_info.device),
        str(port_info.description),
        str(port_info.manufacturer),
        str(port_info.hwid),
    ]).lower()

    score = 0

    # Bluetooth priority
    if "bluetooth" in text:
        score += 200
    if "standard serial over bluetooth link" in text:
        score += 300
    if "outgoing" in text:
        score += 50
    if "incoming" in text:
        score -= 30

    # USB / ESP priority
    if "usb" in text:
        score += 80
    if "silicon labs" in text:
        score += 60
    if "cp210" in text:
        score += 60
    if "ch340" in text:
        score += 60
    if "esp32" in text:
        score += 100

    return score


def get_sorted_ports():
    ports = list(list_ports.comports())
    ports.sort(key=score_port, reverse=True)
    return ports


def try_open_port(port_info):
    port_name = port_info.device
    desc = port_info.description

    print("Қосылу:", port_name, "|", desc)

    try:
        ser = serial.Serial(port_name, BAUD, timeout=1)
        time.sleep(2)

        start = time.time()
        while time.time() - start < 6:
            raw = ser.readline().decode("utf-8", errors="ignore")
            line = extract_valid_line(raw)

            if line is None:
                continue

            print(f"[{port_name}] {line}")

            if line == "READY" or is_sensor_line(line) or is_battery_line(line):
                print("ESP32 табылды:", port_name)
                return ser

        ser.close()
        return None

    except Exception as e:
        print("Қате:", port_name, e)
        return None


def connect_esp32():
    while True:
        ports = get_sorted_ports()

        print("Порттар:")
        for p in ports:
            print(" ", p.device, "|", p.description)

        for p in ports:
            ser = try_open_port(p)
            if ser is not None:
                return ser

        print("ESP32 табылмады, қайта іздеу...")
        time.sleep(2)


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Pygame күтілуде: {HOST}:{PORT}")
    return server


def wait_client(server):
    while True:
        client, addr = server.accept()
        print("Pygame қосылды:", addr)
        return client


def main():
    server = start_server()
    client = None
    ser = None

    while True:
        try:
            if client is None:
                client = wait_client(server)

            if ser is None or not ser.is_open:
                ser = connect_esp32()

            raw = ser.readline().decode("utf-8", errors="ignore")
            line = extract_valid_line(raw)

            if line is None:
                continue

            print("ESP32:", line)
            client.sendall((line + "\n").encode("utf-8"))

        except KeyboardInterrupt:
            print("Тоқтатылды")
            break

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print("Pygame ажырады:", e)
            try:
                if client:
                    client.close()
            except Exception:
                pass
            client = None
            time.sleep(1)

        except Exception as e:
            print("Жалпы қате:", e)
            try:
                if ser and ser.is_open:
                    ser.close()
            except Exception:
                pass
            ser = None
            time.sleep(2)

    try:
        if client:
            client.close()
    except Exception:
        pass

    try:
        if ser and ser.is_open:
            ser.close()
    except Exception:
        pass

    try:
        server.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()