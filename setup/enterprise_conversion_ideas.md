# ideas for how to deploy.make this better on the enterprise side.

Done via MAKE

make a dedicated deploy box with a snapshot for testing this, don't do in dev.

## Server:
- to /opt/longhaulc2/server....
> readonly for users

Systemd service: `longhaulc2-server`
> Created by makefile

## Client:
- to /opt/longhaulc2/web....
> readonly for users

Systemd service: `longhaulc2-web`
> Created by makefile


# Logs:
/var/log/longhaulc2/server/...
/var/log/longhaulc2/web/...

## User:
Create a service user with no shell jsut in case
`useradd --system --no-create-home --shell /bin/false longhaul`



# finally, start both services/have an output that starts them
`systemctl daemon-reload`
`systemctl start longhaulc2-server`
`systemctl start longhaulc2-web`


