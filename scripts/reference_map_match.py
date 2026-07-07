import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.reference_map.matcher import generate_candidate_assignments, write_candidate_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description='Deterministic candidate matcher (Milestone 3).')
    parser.add_argument('--sample-limit', type=int, default=None, help='Limit extracted signs processed for sample run.')
    args = parser.parse_args()

    output = generate_candidate_assignments(ROOT, sample_limit=args.sample_limit)
    paths = write_candidate_outputs(ROOT, output)

    print('reference_matcher_ok', True)
    print('sample_limit', output['sample_limit'])
    print('approved_reference_positions', output['summary']['approved_reference_positions'])
    print('extracted_sample_size', output['summary']['extracted_sample_size'])
    print('candidate_count', output['summary']['candidate_count'])
    print('candidate_file', paths['candidate_file'])
    print('manifest_file', paths['manifest_file'])


if __name__ == '__main__':
    main()
