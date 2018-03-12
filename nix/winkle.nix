{pkgs, postShellHook ? "", extraDeps ? []}:
let
	python = import ./requirements.nix { inherit pkgs; };
	version_pat = "version[[:space:]]*=[[:space:]]*\"([0-9.]+)\"[[:space:]]*";
	version = builtins.elemAt (builtins.match version_pat (builtins.readFile ../winkle/version.py)) 0;
in python.mkDerivation {
	name = "winkle-${version}";
	src = ../.;
	buildInputs = [
		python.packages."aiohttp"
		python.packages."yamlcfg"
	] ++ extraDeps;
	inherit postShellHook;
}
