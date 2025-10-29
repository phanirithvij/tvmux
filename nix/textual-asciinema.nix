{
  lib,
  python3,
  fetchFromGitHub,
  textual-tty,
}:

python3.pkgs.buildPythonPackage {
  pname = "textual-asciinema";
  version = "0.0.4-unstable-2025-08-18";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "ttygroup";
    repo = "textual-asciinema";
    rev = "e0e873757c5ade417c25b024fb3ded5f8e296143";
    hash = "sha256-hvbYgClw7c+h8holD2DvZS3cfSxYxJuRQ33Tt5YscfM=";
  };

  build-system = with python3.pkgs; [
    flit-core
  ];

  dependencies =
    with python3.pkgs;
    [
      platformdirs
      textual
    ]
    ++ [
      textual-tty
    ];

  optional-dependencies = {
    dev = with python3.pkgs; [
      build
      coverage
      mkdocs
      mkdocs-material
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
    "textual_asciinema"
  ];

  meta = {
    description = "Asciinema video widget for textual";
    homepage = "https://github.com/ttygroup/textual-asciinema";
    license = lib.licenses.wtfpl;
    maintainers = with lib.maintainers; [ phanirithvij ];
  };
}
