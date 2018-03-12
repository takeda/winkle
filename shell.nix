{ nixpkgs ? <nixpkgs> }:
let
	pkgs = import nixpkgs {};
	callPackage = pkgs.lib.callPackageWith (pkgs // pythonPkgs);
	pythonPkgs = {
		winkle = callPackage nix/winkle.nix {
			postShellHook = ''
				export CDE_HOME=$(pwd)/cde
				cd $CDE_HOME
				function finish {
					make clean
				}
				trap finish EXIT
				make consul-start
			'';
			extraDeps = [
				pkgs.haproxy
				pkgs.consul
			];
		};
	};
in pythonPkgs
