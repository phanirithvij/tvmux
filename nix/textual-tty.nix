{
  lib,
  python3,
  fetchFromGitHub,
  bittty,
  textual-window,
}:

python3.pkgs.buildPythonPackage rec {
  pname = "textual-tty";
  version = "0.2.2";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "ttygroup";
    repo = "textual-tty";
    rev = version;
    hash = "sha256-tyn0bmgbh5ZyjP8hcFA3CTdHoU/8nGoeG5m+d3Zl8Ac=";
  };

  build-system = with python3.pkgs; [
    flit-core
  ];

  dependencies =
    with python3.pkgs;
    [
      textual
      #pywinpty # windows-only
    ]
    ++ [
      bittty
      textual-window
    ];

  optional-dependencies = {
    dev = with python3.pkgs; [
      build
      coverage
      mkdocs
      pre-commit
      pydoc-markdown
      pytest
      pytest-asyncio
      pytest-cov
      ruff
      twine
    ];
  };

  pythonImportsCheck = [
    "textual_tty"
  ];

  meta = {
    description = "A pure python terminal for textual";
    homepage = "https://github.com/ttygroup/textual-tty";
    license = lib.licenses.wtfpl;
    maintainers = with lib.maintainers; [ phanirithvij ];
  };
}
