{
  description = "HTTP Proxy Dev Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f {
      pkgs = import nixpkgs { inherit system; };
    });
  in {
    devShells = forAllSystems ({ pkgs }: {
      default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python3
          python3Packages.requests
          python3Packages.flask
          git
          curl
          wireshark
        ];

        shellHook = ''
          echo "HTTP Proxy Dev Environment ready"
        '';
      };
    });
  };
}
