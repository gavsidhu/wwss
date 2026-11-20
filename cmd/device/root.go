package device

import (
	"github.com/spf13/cobra"
)

var (
	deviceName        string
	deviceIPv4        string
	deviceMAC         string
	deviceHost        string
	deviceTailscaleIP string
)

var DeviceCmd = &cobra.Command{
	Use:   "device",
	Short: "Manage saved devices",
	Long: `Add, list, update, and delete devices stored in the wwss config.

A device needs a name, a local IPv4 address, and a MAC address. Hostname and Tailscale IP are optional.`,
}

func init() {
	DeviceCmd.AddCommand(deviceCmd)
	DeviceCmd.AddCommand(deleteCmd)
	DeviceCmd.AddCommand(listCmd)
	DeviceCmd.AddCommand(updateCmd)

}
