# Wildcard DNS server

This is an authorative wildcard DNS server, which allows you to host a nip.io / xip.io style service locally.

It is based on https://github.com/GrahamDumpleton/wildcard-dns-server , with a main difference being
this one is authorative, while the original is meant to act as a proxy resolver.

It resolves addresses like this:
`foo.10.10.10.10.<yourdomain>`
to
10.10.10.10.

To configure the server, you need to add two DNS records in your local DNS server:

1) an A record pointing to the machine on which you installed the server, for example ns.nip.local
2) an NS record on nip.local (or whatever domain you use) pointing to ns.nip.local (what you used in step #1)

You can edit the configuration parameters in server.py or use environment variables.

## configuration envrionment variables
`WILDCARD_DOMAIN` - the wildcard domain root, eg. nip.local
`NS_DOMAIN` - the DNS name pointing to the machine running the server
`MY_IP` - the IP address of the machine running the server
`DNS_PORT` - port to listen on. Defaults to 10053 for development (set to 53 for real usage)
`DEBUG_LEVEL` - enable debug output if set to more than 0. more verbose as the number goes up.
