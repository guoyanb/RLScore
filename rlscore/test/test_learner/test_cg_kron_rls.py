import unittest

import numpy as np
from rlscore.measure import auc
from rlscore.measure import sqerror
from rlscore.kernel import GaussianKernel
from rlscore.kernel import LinearKernel
from rlscore.learner.conditional_ranking import ConditionalRanking
from rlscore.learner.kron_rls import KronRLS, PairwiseModelLinearHack
from rlscore.learner.cg_kron_rls import CGKronRLS
from rlscore.learner.rls import RLS
from rlscore.learner.label_rankrls import LabelRankRLS


class Test(unittest.TestCase):
    
    def setUp(self):
        np.random.seed(55)
        #random.seed(100)
    
    
    def generate_data(self, poscount, negcount, dim, mean1, mean2):
        #Generates a standard binary classification data set,
        #with poscount+negcount instances. Data is normally
        #distributed, with mean1 for positive class,
        #mean2 for negative class and unit variance
        X_pos = np.random.randn(poscount, dim)+mean1
        X_neg = np.random.randn(negcount, dim)+mean2
        X = np.vstack((X_pos, X_neg))
        Y = np.vstack((np.ones((poscount, 1)), -1.*np.ones((negcount,1))))
        perm = np.random.permutation(range(poscount+negcount))
        X = X[perm]
        Y = Y[perm]
        return X, Y
    
    
    def generate_xortask(self):
        np.random.seed(55)
        trainpos1 = 5
        trainneg1 = 5
        trainpos2 = 6
        trainneg2 = 7
        X_train1, Y_train1 = self.generate_data(trainpos1, trainneg1, 5, 0, 1)
        X_train2, Y_train2 = self.generate_data(trainpos2, trainneg2, 5, 4, 6)
        
        testpos1 = 26
        testneg1 = 27
        testpos2 = 25
        testneg2 = 25
        X_test1, Y_test1 = self.generate_data(testpos1, testneg1, 5, 0, 1)
        X_test2, Y_test2 = self.generate_data(testpos2, testneg2, 5, 4, 6)
        
        #kernel1 = GaussianKernel.createKernel(gamma=0.01, train_features=X_train1)
        kernel1 = LinearKernel.createKernel(train_features=X_train1)
        K_train1 = kernel1.getKM(X_train1)
        K_test1 = kernel1.getKM(X_test1)
        
        #kernel2 = GaussianKernel.createKernel(gamma=0.01, train_features=X_train2)
        kernel2 = LinearKernel.createKernel(train_features=X_train2)
        K_train2 = kernel2.getKM(X_train2)
        K_test2 = kernel2.getKM(X_test2)
        
        #The function to be learned is a xor function on the class labels
        #of the two classification problems
        Y_train = -1.*np.ones((trainpos1+trainneg1, trainpos2+trainneg2))
        for i in range(trainpos1+trainneg1):
            for j in range(trainpos2+trainneg2):
                if Y_train1[i,0] != Y_train2[j,0]:
                    Y_train[i, j] = 1.
        
        Y_test = -1.*np.ones((testpos1+testneg1, testpos2+testneg2))    
        for i in range(testpos1+testneg1):
            for j in range(testpos2+testneg2):
                if Y_test1[i,0] != Y_test2[j,0]:
                    Y_test[i, j] = 1.
        
        return K_train1, K_train2, Y_train, K_test1, K_test2, Y_test, X_train1, X_train2, X_test1, X_test2
    
    
    def test_cg_kron_rls(self):
        
        
        regparam = 0.001
        
        K_train1, K_train2, Y_train, K_test1, K_test2, Y_test, X_train1, X_train2, X_test1, X_test2 = self.generate_xortask()
        rows, columns = Y_train.shape
        print K_train1.shape, K_train2.shape, K_test1.shape, K_test2.shape, rows, columns #,'foo'
        trainlabelcount = rows * columns
        indmatrix = np.mat(range(trainlabelcount)).T.reshape(rows, columns)
        
        nonzeros_x_coord = []
        nonzeros_y_coord = []
        nonzeros_x_coord = [0,0,1,1,2,2,3,4,5,6,6,7]
        nonzeros_y_coord = [0,1,0,1,1,2,3,4,4,4,5,5]
        #for i in range(rows):
        #    for j in range(columns):
        #        nonzeros_y_coord.append(i)
        #        nonzeros_x_coord.append(j)
        
        
        Y_train_nonzeros = []
        B = np.mat(np.zeros((len(nonzeros_x_coord),trainlabelcount)))
        for ind in range(len(nonzeros_x_coord)):
            i, j = nonzeros_y_coord[ind], nonzeros_x_coord[ind]
            Y_train_nonzeros.append(Y_train[i, j])
            B[ind, i * columns + j] = 1.
            #B[ind, j * rows + i] = 1.
        print B
        #Y_train_nonzeros = np.array(Y_train_nonzeros)
        Y_train_nonzeros = B * Y_train.reshape(trainlabelcount, 1)
        
        #Train linear Kronecker RLS
        params = {}
        params["regparam"] = regparam
        params["xmatrix1"] = X_train1
        params["xmatrix2"] = X_train2
        params["train_labels"] = Y_train_nonzeros
        params["nonzeros_x_coord"] = nonzeros_x_coord
        params["nonzeros_y_coord"] = nonzeros_y_coord
        linear_kron_learner = CGKronRLS.createLearner(**params)
        linear_kron_learner.train()
        linear_kron_model = linear_kron_learner.getModel()
        linear_kron_testpred = linear_kron_model.predictWithDataMatrices(X_test1, X_test2)
        
        #Train kernel Kronecker RLS
        params = {}
        params["regparam"] = regparam
        params["kmatrix1"] = K_train1
        params["kmatrix2"] = K_train2
        params["train_labels"] = Y_train_nonzeros
        params["nonzeros_x_coord"] = nonzeros_x_coord
        params["nonzeros_y_coord"] = nonzeros_y_coord
        kernel_kron_learner = CGKronRLS.createLearner(**params)
        kernel_kron_learner.train()
        kernel_kron_model = kernel_kron_learner.getModel()
        kernel_kron_testpred = kernel_kron_model.predictWithKernelMatrices(K_test1, K_test2)
        
        #Train an ordinary RLS regressor for reference
        K_Kron_train_x = np.kron(K_train1, K_train2)
        params = {}
        params["kmatrix"] = B * K_Kron_train_x * B.T
        params["train_labels"] = Y_train_nonzeros#Y_train.reshape(trainlabelcount, 1)
        ordrls_learner = RLS.createLearner(**params)
        ordrls_learner.solve(regparam)
        ordrls_model = ordrls_learner.getModel()
        K_Kron_test_x = np.kron(K_test1, K_test2) * B.T
        ordrls_testpred = ordrls_model.predict(K_Kron_test_x)
        ordrls_testpred = ordrls_testpred.reshape(Y_test.shape[0], Y_test.shape[1])
        
        print linear_kron_testpred[0, 0], kernel_kron_testpred[0, 0], ordrls_testpred[0, 0]
        print linear_kron_testpred[0, 1], kernel_kron_testpred[0, 1], ordrls_testpred[0, 1]
        print linear_kron_testpred[1, 0], kernel_kron_testpred[1, 0], ordrls_testpred[1, 0]
        print np.mean(np.abs(linear_kron_testpred - ordrls_testpred)), np.mean(np.abs(kernel_kron_testpred - ordrls_testpred))


