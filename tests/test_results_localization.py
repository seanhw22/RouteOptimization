from django.utils.translation import override

from results.views import _build_conclusion


def test_indonesian_results_conclusion_is_localized():
    results = [
        {'algorithm': 'Greedy', 'distance': 120.0, 'runtime': 2.0, 'violations': 0},
        {'algorithm': 'HGA', 'distance': 100.0, 'runtime': 8.0, 'violations': 1},
    ]
    with override('id'):
        conclusion = _build_conclusion(results, node_count=30)

    assert 'memberikan hasil terbaik' in conclusion
    assert 'Catatan kapasitas' in conclusion
    assert 'Rekomendasi' in conclusion


def test_indonesian_tied_conclusion_uses_algoritma():
    with override('id'):
        conclusion = _build_conclusion([
            {'algorithm': 'Greedy', 'distance': 100.0, 'runtime': 1.0, 'violations': 0},
            {'algorithm': 'HGA', 'distance': 100.0, 'runtime': 2.0, 'violations': 0},
        ], node_count=10)

    assert 'algoritma' in conclusion
    assert 'algoritme' not in conclusion
