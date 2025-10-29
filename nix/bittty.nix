{
  lib,
  python3,
  fetchFromGitHub,
}:

python3.pkgs.buildPythonPackage rec {
  pname = "bittty";
  version = "0.0.5"; # latest is 0.0.9
  pyproject = true;

  src = fetchFromGitHub {
    owner = "bitplane";
    repo = "bittty";
    rev = version;
    hash = "sha256-l2grcf1Qq+P8VkP/qHZ1F4jvCCMwiTJH5stOSU8vHbs=";
  };

  build-system = with python3.pkgs; [
    flit-core
  ];

  dependencies = [
    # pywinpty # windows-only
  ];

  optional-dependencies = {
    dev = with python3.pkgs; [
      build
      coverage
      plotext
      pre-commit
      pydoc-markdown
      pytest
      pytest-asyncio
      pytest-cov
      ruff
      snakeviz
      twine
    ];
  };

  pythonImportsCheck = [
    "bittty"
  ];

  meta = {
    description = "Bitplane tty";
    homepage = "https://github.com/bitplane/bittty";
    license = lib.licenses.wtfpl;
    maintainers = with lib.maintainers; [ phanirithvij ];
  };
}
