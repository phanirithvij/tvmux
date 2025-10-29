{
  lib,
  fetchFromGitHub,
  python3,
}:

python3.pkgs.buildPythonPackage rec {
  pname = "ezpubsub";
  version = "0.3.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "edward-jazzhands";
    repo = "ezpubsub";
    rev = "v${version}";
    hash = "sha256-wW92YutSQvxx7IEeGhR4qfc75CmDL2lcE/j4lOs6Zmg=";
  };

  build-system = with python3.pkgs; [
    uv-build
  ];

  pythonImportsCheck = [
    "ezpubsub"
  ];

  meta = {
    description = "An ultra simple, modern pub/sub library and blinker alternative for Python";
    homepage = "https://github.com/edward-jazzhands/ezpubsub";
    changelog = "https://github.com/edward-jazzhands/ezpubsub/blob/${src.rev}/CHANGELOG.md";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ phanirithvij ];
  };
}
