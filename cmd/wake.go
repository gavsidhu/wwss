package cmd

import (
	"fmt"
	"strings"

	"github.com/gavsidhu/wwss/internal"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var wakeCmd = &cobra.Command{
	Use:   "wake [device name]",
	Args:  cobra.ExactArgs(1),
	Short: "Wake a saved device",
	Long: `Send a Wake-on-LAN magic packet to a device saved in the config.

The device must already exist and have a MAC address:

  wwss wake office-pc`,
	Run: func(cmd *cobra.Command, args []string) {
		deviceName := strings.ToLower(args[0])

		var devices map[string]internal.DeviceConfig

		if err := viper.UnmarshalKey("devices", &devices); err != nil {
			cobra.CheckErr(err)
		}

		device, ok := devices[deviceName]
		if !ok {
			cobra.CheckErr(fmt.Errorf("device %q not found", deviceName))
		}

		if device.MACAddress == "" {
			cobra.CheckErr(fmt.Errorf("device %q has an empty MAC address", deviceName))
		}

		packet, err := internal.NewMagicPacket(device.MACAddress)
		cobra.CheckErr(err)

		cobra.CheckErr(packet.Send(device.LocalIPv4))
		fmt.Println("Magic packet sent")
	},
}

func init() {
	rootCmd.AddCommand(wakeCmd)
}
