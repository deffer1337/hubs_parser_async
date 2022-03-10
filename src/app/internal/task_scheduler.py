import requests


def run_parser(id: int):
    try:
        requests.get(f"http://parser:8080/run_parser?id={id}")
    except Exception as e:
        print(e.__str__())
