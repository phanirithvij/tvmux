{
  lib,
  python3,
  fetchFromGitHub,
  asciinema,
  textual-asciinema,
}:

python3.pkgs.buildPythonApplication {
  pname = "tvmux";
  version = "0.6.0-unstable-2025-08-20";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "bitplane";
    repo = "tvmux";
    rev = "388533b8c6ccbab1391cbac2da8695e26532ffb1";
    hash = "sha256-xNTBheKOq47dyyWaZYLfnFibU6tpFWvSZKtw9W10Be8=";
  };

  patches = [ ./tvmux-server-binary.patch ];

  postPatch = ''
    substituteInPlace src/tvmux/connection.py \
      --replace '["python", "-m", "tvmux.server.main"]' "[\"$out/bin/tvmux-server\"]"
  '';

  build-system = [
    python3.pkgs.flit-core
  ];

  dependencies =
    with python3.pkgs;
    [
      click
      fastapi
      httpx
      psutil
      pydantic
      requests
      textual
      tomli
      tomli-w
      uvicorn
    ]
    ++ [
      asciinema
      textual-asciinema
    ];

  optional-dependencies = with python3.pkgs; {
    dev = [
      build
      coverage
      pre-commit
      pydoc-markdown
      pytest
      pytest-cov
      ruff
      twine
    ];
  };

  pythonImportsCheck = [
    "tvmux"
  ];

  meta = {
    description = "A tmux session recorder using asciinema";
    homepage = "https://github.com/bitplane/tvmux";
    license = lib.licenses.wtfpl;
    maintainers = with lib.maintainers; [ phanirithvij ];
    mainProgram = "tvmux";
  };
}
