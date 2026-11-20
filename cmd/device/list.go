package device

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Args:  cobra.NoArgs,
	Short: "List saved devices",
	Long: `Print the names of devices stored in the wwss config.

  wwss device list`,
	Run: func(cmd *cobra.Command, args []string) {
		deviceMap := viper.GetStringMap("devices")

		fmt.Println("Devices:")
		for k := range deviceMap {
			fmt.Println(k)
		}

	},
}
