from __future__ import print_function

import os
import sys
import re
import json
import string

from twisted.internet import reactor, defer
from twisted.python import failure
from twisted.names import client, common, authority, dns, error, server

TTL = 60*60*60


class DynamicResolver(authority.FileAuthority):
    """
    A resolver which implements xip.io style IP resolution based on name.
    as well as more conventional glob style DNS wildcard mapping. If no
    match will fallback to specified DNS server for lookup.

    """

    def __init__(self, wildcard_domain, debug_level=0, ns_domain=None, my_ip=None):

        common.ResolverBase.__init__(self)
        self._cache = {}

        self._debug_level = debug_level
        self.ns_domain = ns_domain
        self.wildcard_domain = wildcard_domain
        self.my_ip = bytes(my_ip)

        self.soa = dns.Record_SOA(mname=self.wildcard_domain,
                                  rname=self.wildcard_domain,
                                  serial=0,
                                  refresh=TTL,
                                  minimum=TTL,
                                  expire=TTL * 24,
                                  ttl=TTL)

        # Create regex pattern corresponding to xip.io style DNS
        # wilcard domain.

        pattern = (r'(.*\.)?(?P<ipaddr>\d+\.\d+\.\d+\.\d+)\.%s' %
                   re.escape(wildcard_domain))

        if self._debug_level > 0:
            print('wildcard %s' % pattern, file=sys.stderr)

        self._wildcard = re.compile(pattern)

    def lookupNameservers(self, name, timeout=None):
        """ Answer NS record requests """
        if name.endswith('.' + self.wildcard_domain) or name == self.wildcard_domain:
            payload = dns.Record_NS(name=self.ns_domain)
            answer = dns.RRHeader(name=name, type=dns.NS,
                                  payload=payload, auth=True, ttl=TTL)

            # Additional section: NS ip address
            additional_payload = dns.Record_A(address=self.my_ip)
            additional_answer = dns.RRHeader(name=name,
                                             payload=additional_payload, ttl=TTL)

            answers = [answer]
            authority = []
            additional = [additional_answer]

            return defer.succeed((answers, authority, additional))

        # fail for domains that are not handled by our server
        return defer.fail(failure.Failure(dns.AuthoritativeDomainError(name)))

    def _localLookup(self, name):
        if self._debug_level > 2:
            print('lookup %s' % name, file=sys.stderr)

        # First try and map xip.io style DNS wildcard.

        match = self._wildcard.match(name)

        if match:
            ipaddr = match.group('ipaddr')

            if self._debug_level > 1:
                print('wildcard %s --> %s' % (name, ipaddr), file=sys.stderr)

            return ipaddr

    def _lookup(self, name, cls, type, timeout=None):
        if self._debug_level > 2:
            print('address %s (%s)' % (name, type), file=sys.stderr)

        answers = []
        additional = []
        authority = []

        if type == dns.NS:
            return self.lookupNameservers(name)
        elif type == dns.SOA:
            answer = dns.RRHeader(name=name, type=dns.SOA,
                                  payload=self.soa, auth=True, ttl=TTL)
            return defer.succeed(([answer], authority, additional))
        else:
            result = self._localLookup(name)
            if result:
                # TTL = 1 hour
                payload = dns.Record_A(address=bytes(result))
                answer = dns.RRHeader(name=name, payload=payload, auth=True, ttl=TTL)

                answers = [answer]

                return defer.succeed((answers, authority, additional))

            else:
                if self._debug_level > 2:
                    print('Unknown %s' % name, file=sys.stderr)
                return defer.fail(failure.Failure(dns.AuthoritativeDomainError(name)))


def main():
    wildcard_domain = os.environ.get('WILDCARD_DOMAIN', 'xip.io')
    ns_domain = os.environ.get('NS_DOMAIN', 'ns-1.xip.io')
    my_ip = os.environ.get('MY_IP', '127.0.0.1')
    port = int(os.environ.get('DNS_PORT', '10053'))

    debug_level = int(os.environ.get('DEBUG_LEVEL', '0'))

    factory = server.DNSServerFactory(
        authorities=[DynamicResolver(wildcard_domain=wildcard_domain,
                                     debug_level=debug_level,
                                     ns_domain=ns_domain,
                                     my_ip=my_ip)])

    protocol = dns.DNSDatagramProtocol(controller=factory)

    reactor.listenUDP(port, protocol)
    reactor.listenTCP(port, factory)

    reactor.run()


if __name__ == '__main__':
    raise SystemExit(main())
