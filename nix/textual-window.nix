{
  lib,
  python3,
  fetchFromGitHub,
  ezpubsub,
}:

python3.pkgs.buildPythonPackage rec {
  pname = "textual-window";
  version = "0.8.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "ttygroup";
    repo = "textual-window";
    rev = "v${version}";
    hash = "sha256-Rn4oFRfwgcHGjM3r9hGJsTUKkkdiS7fFC75kaFYfKYY=";
  };

  build-system = with python3.pkgs; [
    hatchling
  ];

  dependencies =
    with python3.pkgs;
    [
      textual
    ]
    ++ [ ezpubsub ];

  pythonImportsCheck = [
    "textual_window"
  ];

  pythonRelaxDeps = [ "textual" ];

  meta = {
    description = "A Textual widget for a floating, draggable window and included window bar/manager system";
    homepage = "https://github.com/ttygroup/textual-window";
    changelog = "https://github.com/ttygroup/textual-window/blob/${src.rev}/CHANGELOG.md";
    license = lib.licenses.unfree; # FIXME: did not find a license
    maintainers = with lib.maintainers; [ phanirithvij ];
  };
}
