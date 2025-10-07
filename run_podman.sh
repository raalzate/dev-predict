podman pull prosody/prosody

podman run -d --name prosody-local \
  -p 5222:5222 \
  -v ./prosody-config:/etc/prosody:Z \
  prosody/prosody