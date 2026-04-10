import requests


def main():
    requests.post(
        "http://localhost:8000/record",
        json={"duration": 5, "filename": "temp.wav"},
        timeout=120,
    )
    response = requests.get(
        "http://localhost:8000/query",
        params={"q": "What did my professor say?"},
        timeout=120,
    )
    print(response.json())


if __name__ == "__main__":
    main()
