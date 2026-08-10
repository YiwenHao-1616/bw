import sys
import datetime
import requests


def main():
    if len(sys.argv) < 5:
        print("usage: python push_to_miaoda.py <txt_file> <source> <edge_url> <sync_key>")
        sys.exit(1)

    txt_file = sys.argv[1]
    source = sys.argv[2]
    edge_url = sys.argv[3]
    sync_key = sys.argv[4]

    if source not in ("huisi", "jiahui"):
        print("error: source must be huisi or jiahui, got: " + str(source))
        sys.exit(1)

    with open(txt_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if len(text) < 20:
        print("error: txt too short (" + str(len(text)) + " chars)")
        sys.exit(1)

    payload = {
        "source": source,
        "date": datetime.date.today().isoformat(),
        "text": text,
    }

    print("[" + source + "] " + str(len(text)) + " chars, pushing to miaoda...")

    try:
        resp = requests.post(
            edge_url,
            json=payload,
            headers={"x-sync-key": sync_key, "Content-Type": "application/json"},
            timeout=300,
        )
        print("[" + source + "] HTTP " + str(resp.status_code))
        print("[" + source + "] " + resp.text)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        print("[" + source + "] error: timeout (300s)")
        sys.exit(2)
    except requests.exceptions.RequestException as e:
        print("[" + source + "] error: " + str(e))
        sys.exit(3)


if __name__ == "__main__":
    main()
