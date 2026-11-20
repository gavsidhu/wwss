package internal

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"strings"
)

func ValidateIPv4(ip string) error {
	if net.ParseIP(ip).To4() == nil {
		return fmt.Errorf("invalid IPv4 address %q", ip)
	}
	return nil
}

func ValidateMAC(mac string) error {
	hw, err := net.ParseMAC(mac)
	if err != nil || len(hw) != 6 {
		return fmt.Errorf("invalid MAC address %q", mac)
	}
	return nil
}

func ConfirmDelete(prompt string) bool {
	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("%s [y/N]: ", prompt)

	input, err := reader.ReadString('\n')
	if err != nil {
		return false
	}

	answer := strings.ToLower(strings.TrimSpace(input))
	return answer == "y" || answer == "yes"
}
