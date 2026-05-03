{
  pkgs,
  lib,
  scripts,
}:
let
  corePython = pkgs.python3.withPackages (ps: [
    ps.jinja2
    ps.pytest
    ps.pytest-mock
    ps.pytest-cov
  ]);
in
pkgs.stdenv.mkDerivation {
  pname = "core-cli";
  version = "1.4.0";
  src = scripts;
  nativeBuildInputs = [ pkgs.makeWrapper ];
  buildInputs = [ corePython ];
  dontBuild = true;
  installPhase = ''
    mkdir -p $out/bin
    cp -r . $out/scripts
    makeWrapper ${corePython}/bin/python3 $out/bin/core-cli \
      --add-flags "$out/scripts/core_cli.py" \
      --set PYTHONPATH "$out/scripts"
  '';

  passthru = {
    python = corePython;
  };

  meta = with lib; {
    description = "Autonomous Organization Core CLI and Agent Runner";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
