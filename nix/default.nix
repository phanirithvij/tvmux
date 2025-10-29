{
  pkgs ? import <nixpkgs> {
    config.allowUnfree = true;
  },
}:
let
  inherit (pkgs) callPackage;
in
callPackage ./tvmux.nix {
  textual-asciinema = callPackage ./textual-asciinema.nix {
    textual-tty = callPackage ./textual-tty.nix {
      bittty = callPackage ./bittty.nix { };
      textual-window = callPackage ./textual-window.nix {
        ezpubsub = callPackage ./ezpubsub.nix { };
      };
    };
  };
}
