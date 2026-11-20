package device

import (
	"fmt"
	"os"
	"strings"

	"github.com/gavsidhu/wwss/internal"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var deviceCmd = &cobra.Command{
	Use:   "add",
	Short: "Save a device",
	Long: `Save a device so it can be woken later.

Name, local IPv4, and MAC address are required. Hostname and Tailscale IP are optional:

  wwss device add --name office-pc --ipv4 192.168.1.20 --mac aa:bb:cc:dd:ee:ff`,
	Run: func(cmd *cobra.Command, args []string) {

		if deviceName == "" {
			fmt.Println("name cannot be empty")
			os.Exit(1)
		}

		if deviceIPv4 == "" {
			fmt.Println("ip cannot be empty")
			os.Exit(1)
		}

		if deviceMAC == "" {
			fmt.Println("mac cannot be empty")
			os.Exit(1)
		}

		cobra.CheckErr(internal.ValidateIPv4(deviceIPv4))
		cobra.CheckErr(internal.ValidateMAC(deviceMAC))

		// TODO: Treat device names as literal keys, or reject names containing dots.
		// Example: add "office.pc", then "other"; a later config write can create
		// an extra, incomplete "office" device through Viper's dotted key paths.
		deviceName = strings.ToLower(deviceName)
		deviceMap := viper.GetStringMap("devices")
		if _, ok := deviceMap[deviceName]; ok {
			fmt.Printf("Device %s already exists, use `wwss device update` to change it\n", deviceName)
			os.Exit(1)
		}

		newDevice := internal.DeviceConfig{
			LocalIPv4:  deviceIPv4,
			MACAddress: deviceMAC,
		}

		if deviceHost != "" {
			newDevice.HostName = deviceHost
		}

		if deviceTailscaleIP != "" {
			newDevice.TailscaleIPAddress = deviceTailscaleIP
		}

		deviceMap[deviceName] = newDevice

		viper.Set("devices", deviceMap)
		cobra.CheckErr(viper.WriteConfig())
	},
}

func init() {
	deviceCmd.Flags().StringVar(&deviceName, "name", "", "Name used to wake and manage the device")
	deviceCmd.Flags().StringVar(&deviceIPv4, "ipv4", "", "Local IPv4 address")
	deviceCmd.Flags().StringVar(&deviceTailscaleIP, "tailscale-ip", "", "Tailscale IP address")
	deviceCmd.Flags().StringVar(&deviceMAC, "mac", "", "MAC address used for Wake-on-LAN")
	deviceCmd.Flags().StringVar(&deviceHost, "hostname", "", "Hostname")

	if err := deviceCmd.MarkFlagRequired("name"); err != nil {
		panic(err)
	}
	if err := deviceCmd.MarkFlagRequired("ipv4"); err != nil {
		panic(err)
	}
	if err := deviceCmd.MarkFlagRequired("mac"); err != nil {
		panic(err)
	}

}
