admins = { "admin@localhost" }
modules_enabled = {
    "roster";
    "saslauth";
    "disco";
    "private";
    "vcard";
}

allow_registration = true

c2s_require_encryption = false
s2s_require_encryption = false

authentication = "internal_plain"

log = {
    info = "/var/log/prosody/prosody.log";
    error = "/var/log/prosody/prosody.err.log";
}

pidfile = "/var/run/prosody/prosody.pid";

VirtualHost "localhost"