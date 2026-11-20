package cmd

import (
	"os"

	"github.com/gavsidhu/wwss/cmd/device"
	"github.com/gavsidhu/wwss/internal"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "wwss",
	Short: "Wake devices on your local network",
	Long: `wwss stores devices and wakes them with a Wake-on-LAN magic packet.

Save a device with its MAC address, then wake it by name:

  wwss device add --name office-pc --ipv4 192.168.1.20 --mac aa:bb:cc:dd:ee:ff
  wwss wake office-pc`,
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(internal.InitConfig)
	rootCmd.AddCommand(device.DeviceCmd)
}
