#!/usr/bin/env bash
# Checks the form of specs/ (specs/README.adoc): every entry is
# README.adoc, constitution.adoc or a directory herdr-manifold#<N>-<slug> with
# a number of its own and a spec.adoc, whose header has :status: draft,
# implemented or dropped and :issue: herdr-manifold#<N> of the directory name;
# an implemented specification has a section with its results.
# Prints every violation; the exit status is 1 if there is any.
#
# usage: scripts/check-specs.sh [repository]   (default: that of the script)
set -eu

results='Results'  # the section an implemented specification has
project='herdr-manifold' # the prefix of issue references and directory names

root=${1:-$(dirname "$0")/..}
fail=0

# bad <path under specs/> <message>
bad() {
	echo "specs/$1: $2" >&2
	fail=1
}

# attr <file> <name>: the value of the attribute in the header of the
# document, the lines before the first empty one
attr() {
	sed -n "1,/^\$/s/^:$2:[[:space:]]*//p" "$1"
}

numbers=' '
for path in "$root"/specs/*; do
	name=${path##*/}
	case $name in README.adoc | constitution.adoc) continue ;; esac
	if [[ ! -d $path || ! $name =~ ^$project#([1-9][0-9]*)-[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
		bad "$name" "neither README.adoc, constitution.adoc nor a directory $project#<N>-<slug>"
		continue
	fi
	number=${BASH_REMATCH[1]}
	if [[ $numbers == *" $number "* ]]; then
		bad "$name" "number $number is taken by another directory"
	fi
	numbers+="$number "
	spec=$path/spec.adoc
	if [[ ! -f $spec ]]; then
		bad "$name" "no spec.adoc"
		continue
	fi
	status=$(attr "$spec" status)
	case $status in
	draft | dropped) ;;
	implemented)
		if ! grep -qx "== $results" "$spec"; then
			bad "$name/spec.adoc" "implemented, but no section \"$results\""
		fi
		;;
	*) bad "$name/spec.adoc" ":status: \"$status\" is not draft, implemented or dropped" ;;
	esac
	value=$(attr "$spec" issue)
	if [[ $value != "$project#$number" ]]; then
		bad "$name/spec.adoc" ":issue: \"$value\" is not $project#$number"
	fi
done
exit $fail
