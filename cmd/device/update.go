package device

import (
	"fmt"
	"os"
	"strings"

	"github.com/gavsidhu/wwss/internal"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var updateCmd = &cobra.Command{
	Use:   "update [device name]",
	Args:  cobra.ExactArgs(1),
	Short: "Update a saved device",
	Long: `Change the stored settings for a device.

Only the fields passed as flags are changed:

  wwss device update office-pc --ipv4 192.168.1.30
  wwss device update office-pc --mac aa:bb:cc:dd:ee:ff --hostname office`,
	Run: func(cmd *cobra.Command, args []string) {
		deviceName := strings.ToLower(args[0])

		var devices map[string]internal.DeviceConfig
		cobra.CheckErr(viper.UnmarshalKey("devices", &devices))

		device, ok := devices[deviceName]
		if !ok {
			fmt.Printf("Device %s does not exist\n", deviceName)
			os.Exit(1)
		}

		flags := cmd.Flags()
		if !flags.Changed("ipv4") && !flags.Changed("mac") && !flags.Changed("hostname") && !flags.Changed("tailscale-ip") {
			fmt.Println("Nothing to update, pass at least one of --ipv4, --mac, --hostname, --tailscale-ip")
			os.Exit(1)
		}

		if flags.Changed("ipv4") {
			cobra.CheckErr(internal.ValidateIPv4(deviceIPv4))
			device.LocalIPv4 = deviceIPv4
		}

		if flags.Changed("mac") {
			cobra.CheckErr(internal.ValidateMAC(deviceMAC))
			device.MACAddress = deviceMAC
		}

		if flags.Changed("hostname") {
			device.HostName = deviceHost
		}

		if flags.Changed("tailscale-ip") {
			device.TailscaleIPAddress = deviceTailscaleIP
		}

		devices[deviceName] = device

		viper.Set("devices", devices)
		// TODO: Make config writes in add/update/delete preserve the original on
		// failure by writing a temporary file before replacing the destination.
		// Example: a failed write (disk full or a file-size limit) can leave the
		// existing .wwss.json truncated and unreadable, losing saved devices.
		cobra.CheckErr(viper.WriteConfig())

		fmt.Println("Device updated")
	},
}

func init() {
	updateCmd.Flags().StringVar(&deviceIPv4, "ipv4", "", "New local IPv4 address")
	updateCmd.Flags().StringVar(&deviceMAC, "mac", "", "New MAC address used for Wake-on-LAN")
	updateCmd.Flags().StringVar(&deviceHost, "hostname", "", "New hostname (pass \"\" to clear)")
	updateCmd.Flags().StringVar(&deviceTailscaleIP, "tailscale-ip", "", "New Tailscale IP address (pass \"\" to clear)")
}
