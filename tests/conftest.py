import hypothesis

hypothesis.settings.register_profile('dev', max_examples=10)
hypothesis.settings.register_profile('dist', max_examples=100)
