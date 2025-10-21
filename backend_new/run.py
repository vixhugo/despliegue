if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    env_port = os.getenv("PORT")

    # Build a list of ports to try: user-specified first, then several fallbacks
    ports = []
    if env_port:
        try:
            ports.append(int(env_port))
        except ValueError:
            print(f"Warning: PORT environment variable is not an integer: {env_port}")

    # default preferred port plus a small range of alternatives (preferir 8003)
    ports.extend([8005, 8002, 8003, 8001, 8004])

    for port in ports:
        try:
            print(f"Arrancando servidor en http://{host}:{port} ...")
            uvicorn.run("app.main:app", host=host, port=port)
            break
        except OSError as e:
            # Commonly raised when the port is already in use
            print(f"No se pudo enlazar en {host}:{port} -> {e}. Probando siguiente puerto...")
    else:
        print("No se pudo arrancar el servidor: todos los puertos intentados estÃ¡n en uso. Establece la variable PORT a un puerto libre y vuelve a intentarlo.")