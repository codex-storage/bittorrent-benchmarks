# from benchmarks.core.utils import megabytes
# from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
# from benchmarks.core.experiments.tests.utils import mock_sampler
#
#
# def test_should_run_with_a_single_seeder(deluge_node1, deluge_node2, deluge_node3):
#     network = [deluge_node1, deluge_node2, deluge_node3]
#     experiment = StaticDisseminationExperiment(
#         network=network,
#         seeders=1,
#         sampler=mock_sampler([1]),
#         generator=RandomTempFileGenerator(size=megabytes(50))
#     )
#
#     ready = experiment.setup()
#     ready.run()
