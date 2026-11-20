package device

import (
	"fmt"
	"os"
	"strings"

	"github.com/gavsidhu/wwss/internal"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var deleteCmd = &cobra.Command{
	Use:   "delete [device name]",
	Args:  cobra.ExactArgs(1),
	Short: "Delete a saved device",
	Long: `Remove a device from the wwss config.

You will be asked to confirm before the device is deleted:

  wwss device delete office-pc`,
	Run: func(cmd *cobra.Command, args []string) {

		deviceName := strings.ToLower(args[0])

		deviceMap := viper.GetStringMap("devices")
		if _, ok := deviceMap[deviceName]; !ok {
			fmt.Printf("Device %s does not exist\n", deviceName)
			os.Exit(1)
		}

		if !internal.ConfirmDelete(fmt.Sprintf("Delete device: %s", deviceName)) {
			fmt.Println("Delete canceled")
			os.Exit(1)
		}

		// TODO: Reload and mutate config under a cross-process lock after the
		// confirmation prompt; apply the same protection to add and update.
		// Example: leave the prompt unanswered, add "new-pc" in another terminal,
		// then confirm deletion; writing this old snapshot also removes "new-pc".
		delete(deviceMap, deviceName)

		viper.Set("devices", deviceMap)
		cobra.CheckErr(viper.WriteConfig())

		fmt.Println("Device deleted")

	},
}
