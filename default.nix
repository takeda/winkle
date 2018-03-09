{nixpkgs ? <nixpkgs>}:
let
	pkgs = import nixpkgs {};
	python = import ./requirements.nix { inherit pkgs; };
	version_pat = "version[[:space:]]*=[[:space:]]*\"([0-9.]+)\"[[:space:]]*";
	version = builtins.elemAt (builtins.match version_pat (builtins.readFile winkle/version.py)) 0;
in python.mkDerivation {
	name = "winkle-${version}";
	src = ./.;
	propagatedBuildInputs = [
		python.packages."aiohttp"
		python.packages."yamlcfg"
		pkgs.haproxy
		pkgs.consul
	];
	postShellHook = ''
		export CDE_HOME=$(pwd)/cde
		cd $CDE_HOME
		function finish {
			make clean
		}
		trap finish EXIT
		make consul-start
	'';
}
