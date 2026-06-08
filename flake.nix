{
  description = "HTTP Proxy Dev Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    devShells.default = let
      pkgs = import nixpkgs { system = "x86_64-linux"; };
    in pkgs.mkShell {
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
  };
}
