package internal

import "testing"

func TestValidateIPv4(t *testing.T) {
	tests := []struct {
		ip      string
		wantErr bool
	}{
		{"192.168.1.20", false},
		{"10.0.0.1", false},
		{"", true},
		{"999.1.1.1", true},
		{"192.168.1", true},
		{" 192.168.1.20", true},
		{"fe80::1", true},
		{"office-pc", true},
	}

	for _, tt := range tests {
		t.Run(tt.ip, func(t *testing.T) {
			err := ValidateIPv4(tt.ip)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateIPv4(%q) error = %v, wantErr %v", tt.ip, err, tt.wantErr)
			}
		})
	}
}

func TestValidateMAC(t *testing.T) {
	tests := []struct {
		mac     string
		wantErr bool
	}{
		{"aa:bb:cc:dd:ee:ff", false},
		{"AA-BB-CC-DD-EE-FF", false},
		{"aabb.ccdd.eeff", false},
		{"", true},
		{"nope", true},
		{"aa:bb:cc:dd:ee", true},
		{"aa:bb:cc:dd:ee:ff:00:11", true},
	}

	for _, tt := range tests {
		t.Run(tt.mac, func(t *testing.T) {
			err := ValidateMAC(tt.mac)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateMAC(%q) error = %v, wantErr %v", tt.mac, err, tt.wantErr)
			}
		})
	}
}
