import argparse
import logging

import uvicorn

from wechat_butler.config import ConfigManager
from wechat_butler.server import create_app


def main():
    parser = argparse.ArgumentParser(description="WeChat Butler AI Service")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--port", type=int, default=None, help="Override server port")
    parser.add_argument("--host", default=None, help="Override server host")
    args = parser.parse_args()

    config = ConfigManager(args.config)

    host = args.host or config.config.server.host
    port = args.port or config.config.server.port
    log_level = config.config.server.log_level

    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    app = create_app(config)

    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


if __name__ == "__main__":
    main()
