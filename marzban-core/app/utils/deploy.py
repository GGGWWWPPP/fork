import asyncssh
import asyncio
from app import logger
from app.db import crud

async def deploy_node_via_ssh(node_id: int, host: str, port: int, username: str, password: str = None, key: str = None):
    try:
        from app.db.database import SessionLocal
        db = SessionLocal()
        node = crud.get_node(db, node_id)
        if not node:
            return

        logger.info(f"Starting SSH deployment for node {node.name} at {host}:{port}")

        # Connect via SSH
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None
        }
        if password:
            connect_kwargs["password"] = password
        if key:
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(key)]

        async with asyncssh.connect(**connect_kwargs) as conn:
            # Install Docker if not installed
            await conn.run('curl -fsSL https://get.docker.com | sh', check=False)
            
            # Setup marzban-node directory
            await conn.run('mkdir -p /var/lib/marzban-node/ssl')
            
            # Write docker-compose.yml
            docker_compose = """
services:
  marzban-node:
    image: gozargah/marzban-node:latest
    restart: always
    network_mode: host
    environment:
      SERVICE_PORT: 62050
      XRAY_API_PORT: 62051
      SSL_CERT_FILE: "/var/lib/marzban-node/ssl/client.pem"
      SSL_KEY_FILE: "~"
      SSL_CLIENT_CERT_FILE: "/var/lib/marzban-node/ssl/client.pem"
    volumes:
      - /var/lib/marzban-node:/var/lib/marzban-node
"""
            await conn.run(f'cat <<EOF > /var/lib/marzban-node/docker-compose.yml\n{docker_compose}\nEOF')

            # Fetch certificate from DB
            tls = crud.get_tls_certificate(db)
            cert = tls.certificate
            await conn.run(f'cat <<EOF > /var/lib/marzban-node/ssl/client.pem\n{cert}\nEOF')

            # Start marzban-node
            await conn.run('cd /var/lib/marzban-node && docker compose up -d')
            
            logger.info(f"Node {node.name} deployment finished successfully.")
            node.status = "connected"
            node.message = "Deployed via SSH"
            db.commit()
            
            # Trigger reconnect in marzban master
            from app import xray
            xray.operations.connect_node(node.id)

    except Exception as e:
        logger.error(f"Failed to deploy node {node_id} via SSH: {str(e)}")
        if node:
            node.status = "error"
            node.message = f"SSH Deploy failed: {str(e)}"
            db.commit()
    finally:
        db.close()
