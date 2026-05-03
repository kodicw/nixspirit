{
  pkgs,
  lib,
  scripts,
}:
let
  spiritPython = pkgs.python3.withPackages (ps: [
    ps.jinja2
    ps.pytest
    ps.pytest-mock
    ps.pytest-cov
  ]);
in
pkgs.stdenv.mkDerivation {
  pname = "spirit-cli";
  version = "1.3.0";
  src = scripts;
  nativeBuildInputs = [ pkgs.makeWrapper ];
  buildInputs = [ spiritPython ];
  dontBuild = true;
  installPhase = ''
    mkdir -p $out/bin
    cp -r . $out/scripts
    makeWrapper ${spiritPython}/bin/python3 $out/bin/spirit \
      --add-flags "$out/scripts/spirit_cli.py" \
      --set PYTHONPATH "$out/scripts"
  '';

  passthru = {
    python = spiritPython;
  };

  meta = with lib; {
    description = "spirit Centralized CLI and Agent Runner";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
