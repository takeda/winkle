{ nixpkgs ? <nixpkgs> }:
let
	pkgs = import nixpkgs {};
	callPackage = pkgs.lib.callPackageWith (pkgs // pythonPkgs);
	pythonPkgs = {
		winkle = callPackage nix/winkle.nix {};
	};
in pythonPkgs
