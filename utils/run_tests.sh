#!/bin/sh -e

cd "$(dirname "$0")/.."

echo "=== Nuking old .pyc files..."
find vumi/ -name '*.pyc' -delete
echo "=== Erasing previous coverage data..."
coverage erase
echo "=== Running trial tests..."
coverage run `which trial` --reporter=subunit "${@:-vumi}" | tee results.txt | subunit2pyunit
subunit-stats <results.txt
subunit2junitxml <results.txt >test_results.xml
rm results.txt
echo "=== Processing coverage data..."
coverage xml
echo "=== Checking for PEP-8 violations..."
pep8 --repeat --exclude='migrations' vumi | tee pep8.txt
echo "=== Done."
