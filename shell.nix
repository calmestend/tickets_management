with import <nixpkgs> {};

mkShell {
  buildInputs = [
    python312
    mariadb-connector-c
    gcc
    zsh
  ];

  shellHook = ''
    export MARIADB_CONFIG=${mariadb-connector-c}/bin/mariadb_config
    echo ">> mariadb_config found at: $MARIADB_CONFIG"

		echo ">> Creating virtual environment..."
		python3 -m venv .venv

    echo ">> Activating virtual environment..."
    source .venv/bin/activate

    if [ -f requirements.txt ]; then
      echo ">> Installing dependencies from requirements.txt..."
      pip install --upgrade pip
      pip install -r requirements.txt
    fi

    exec zsh
  '';
}

