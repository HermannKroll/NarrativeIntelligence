import random
from snorkel.learning import GridSearch

class RandomSearchGPU(GridSearch):
    """
    A GridSearch over a random subsample of the hyperparameter search space.

    :param seed: A seed for the GridSearch instance
    """
    def __init__(self, model_class, parameter_dict, X_train, Y_train=None, n=10,
        model_class_params={}, model_hyperparams={}, seed=123, 
        save_dir='checkpoints'):
        """Search a random sample of size n from a parameter grid"""
        self.rand_state = np.random.RandomState()
        self.rand_state.seed(seed)
        self.n = n
        random.seed(seed)
        super(RandomSearchGPU, self).__init__(model_class, parameter_dict, X_train,
            Y_train=Y_train, model_class_params=model_class_params,
            model_hyperparams=model_hyperparams, save_dir=save_dir)

#    def search_space(self):
#        return list(zip(*[self.rand_state.choice(self.parameter_dict[pn], self.n)
#            for pn in self.param_names]))
    
    def search_space(self):
        return list(zip(*[random.choices(self.parameter_dict[pn], k=self.n)
            for pn in self.param_names]))


