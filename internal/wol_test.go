package internal

import (
	"bytes"
	"net"
	"testing"
)

func TestNewMagicPacket(t *testing.T) {
	want := []byte{0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff}

	for _, mac := range []string{"aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF", "aabb.ccdd.eeff"} {
		t.Run(mac, func(t *testing.T) {
			packet, err := NewMagicPacket(mac)
			if err != nil {
				t.Fatalf("NewMagicPacket(%q) returned error: %v", mac, err)
			}

			if !bytes.Equal(packet[:6], []byte{0xff, 0xff, 0xff, 0xff, 0xff, 0xff}) {
				t.Errorf("header = % x, want ff ff ff ff ff ff", packet[:6])
			}

			for i := range 16 {
				offset := 6 + i*6
				if got := packet[offset : offset+6]; !bytes.Equal(got, want) {
					t.Errorf("repetition %d = % x, want % x", i, got, want)
				}
			}
		})
	}
}

func TestNewMagicPacketInvalid(t *testing.T) {
	for _, mac := range []string{
		"",
		"nope",
		"aa:bb:cc:dd:ee",
		"aa:bb:cc:dd:ee:ff:00:11",
	} {
		t.Run(mac, func(t *testing.T) {
			if _, err := NewMagicPacket(mac); err == nil {
				t.Errorf("NewMagicPacket(%q) returned no error", mac)
			}
		})
	}
}

func interfaceAddr(t *testing.T, cidr string) *net.IPNet {
	t.Helper()

	ip, ipNet, err := net.ParseCIDR(cidr)
	if err != nil {
		t.Fatalf("ParseCIDR(%q): %v", cidr, err)
	}
	ipNet.IP = ip
	return ipNet
}

func TestBroadcastAddressFrom(t *testing.T) {
	addrs := []net.Addr{
		&net.IPAddr{IP: net.ParseIP("192.168.1.50")},
		interfaceAddr(t, "127.0.0.1/8"),
		interfaceAddr(t, "fe80::1/64"),
		interfaceAddr(t, "192.168.1.50/24"),
		interfaceAddr(t, "10.20.30.40/16"),
		&net.IPNet{IP: net.ParseIP("172.16.5.1"), Mask: net.CIDRMask(120, 128)},
	}

	tests := []struct {
		name       string
		deviceIPv4 string
		want       string
	}{
		{"/24 subnet", "192.168.1.20", "192.168.1.255"},
		{"/16 subnet", "10.20.99.1", "10.20.255.255"},
		{"16-byte mask", "172.16.5.9", "172.16.5.255"},
		{"not on a local subnet", "10.99.99.99", "255.255.255.255"},
		{"empty IP", "", "255.255.255.255"},
		{"IPv6 device", "fe80::2", "255.255.255.255"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := broadcastAddressFrom(tt.deviceIPv4, addrs)
			if !got.Equal(net.ParseIP(tt.want)) {
				t.Errorf("broadcastAddressFrom(%q) = %s, want %s", tt.deviceIPv4, got, tt.want)
			}
		})
	}
}

func TestBroadcastAddressFromNoInterfaces(t *testing.T) {
	if got := broadcastAddressFrom("192.168.1.20", nil); !got.Equal(net.IPv4bcast) {
		t.Errorf("broadcastAddressFrom with no interfaces = %s, want 255.255.255.255", got)
	}
}
