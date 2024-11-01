def send_message_with_code(message, code) -> None:
    message = f"{message} {code}"
    send_message(message)

def send_message(message) -> None:
    print(f"Sending message: {message}")