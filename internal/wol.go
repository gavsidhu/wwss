package internal

import (
	"errors"
	"net"
)

type MagicPacket [102]byte

func NewMagicPacket(target string) (packet MagicPacket, err error) {
	mac, err := net.ParseMAC(string(target))
	if err != nil {
		return packet, err
	}

	if len(mac) != 6 {
		return packet, errors.New("invalid EUI-48 MAC address")
	}

	copy(packet[0:], []byte{255, 255, 255, 255, 255, 255})
	offset := 6

	for range 16 {
		copy(packet[offset:], mac)
		offset += 6
	}

	return packet, nil
}

func SendMagicPacket(mp MagicPacket, target string) error {
	conn, err := net.Dial("udp4", target)
	if err != nil {
		return err
	}
	defer conn.Close()

	_, err = conn.Write(mp[:])
	return err
}

func (mp MagicPacket) Send(deviceIPv4 string) error {
	return SendMagicPacket(mp, net.JoinHostPort(broadcastAddress(deviceIPv4).String(), "9"))
}

// broadcastAddress returns the broadcast address of the local subnet that
// contains deviceIPv4, or the limited broadcast address if none does.
func broadcastAddress(deviceIPv4 string) net.IP {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return net.IPv4bcast
	}

	return broadcastAddressFrom(deviceIPv4, addrs)
}

func broadcastAddressFrom(deviceIPv4 string, addrs []net.Addr) net.IP {
	target := net.ParseIP(deviceIPv4).To4()
	if target == nil {
		return net.IPv4bcast
	}

	for _, addr := range addrs {
		ipNet, ok := addr.(*net.IPNet)
		if !ok {
			continue
		}

		ip := ipNet.IP.To4()
		if ip == nil || !ipNet.Contains(target) {
			continue
		}

		mask := ipNet.Mask
		if len(mask) == net.IPv6len {
			mask = mask[12:]
		}

		broadcast := make(net.IP, net.IPv4len)
		for i := range broadcast {
			broadcast[i] = ip[i] | ^mask[i]
		}
		return broadcast
	}

	return net.IPv4bcast
}
