package internal

import (
	"errors"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var config_version int = 1

type Config struct {
	Devices       map[string]DeviceConfig `mapstructure:"devices" json:"devices"`
	ConfigVersion int                     `mapstructure:"config_version" json:"config_version"`
}

type DeviceConfig struct {
	LocalIPv4          string `mapstructure:"local_ip_address" json:"local_ip_address"`
	TailscaleIPAddress string `mapstructure:"tailscale_ip_address" json:"tailscale_ip_address"`
	MACAddress         string `mapstructure:"mac_address" json:"mac_address"`
	HostName           string `mapstructure:"hostname" json:"hostname"`
}

func InitConfig() {
	home, err := os.UserHomeDir()
	cobra.CheckErr(err)

	viper.AddConfigPath(home)
	viper.SetConfigName(".wwss")
	viper.SetConfigType("json")
	viper.SetDefault("config_version", config_version)

	viper.SetDefault("devices", map[string]DeviceConfig{})

	if err := viper.ReadInConfig(); err != nil {
		var configFileNotFoundError viper.ConfigFileNotFoundError
		if errors.As(err, &configFileNotFoundError) {
			cobra.CheckErr(viper.SafeWriteConfig())
		} else {
			cobra.CheckErr(err)
		}

	}
}
