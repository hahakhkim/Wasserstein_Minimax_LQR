import numpy as np
import math
from scipy import linalg

def matmul3(A,B,C):
    return np.matmul(A,np.matmul(B,C))


def matmul4(A,B,C,D):
    return np.matmul(np.matmul(A,B),np.matmul(C,D))


def matmul5(A,B,C,D,E):
    return matmul3(np.matmul(A,B),np.matmul(C,D),E)


def matmul6(A,B,C,D,E,F):
    return np.matmul(matmul3(A,B,C), matmul3(D,E,F))


def matmul7(A,B,C,D,E,F,G):
    return matmul3(A,matmul3(B,C,D),matmul3(E,F,G))

def continuous_to_discrete_zoh(A, B, dt):
    A = np.array(A)
    B = np.array(B)
    exp_up = np.hstack((A, B))
    exp_down = np.hstack((np.zeros((B.shape[1], A.shape[0])), np.zeros((B.shape[1], B.shape[1]))))
    exp = np.vstack((exp_up, exp_down))
    exp_result = linalg.expm(dt * exp)
    Ad = exp_result[:A.shape[0], 0:A.shape[1]]
    Bd = exp_result[:A.shape[0], A.shape[1]:]
    return Ad, Bd

def generate_single_sample(sample_number, dim, mean, sigma):
    sample = np.zeros((sample_number, dim, 1))
    for index in range(sample_number):
        sample[index] = np.reshape(np.random.normal(mean, sigma, dim), (dim, 1))
    sample_mean = np.mean(sample, axis=0)
    sample_sigma = np.zeros((dim, dim))
    for index in range(sample_number):
        sample_temp = sample[index]
        sample_sigma = sample_sigma + np.matmul(sample_temp, np.transpose(sample_temp))
    sample_sigma = sample_sigma / sample_number
    return sample, sample_mean, sample_sigma


def generate_multi_sample(sample_number, stage_number, dim, mean, sigma):
    multi_sample = []
    multi_sample_mean = []
    for t in range(stage_number):
        sample, sample_mean, sample_sigma = generate_single_sample(sample_number, dim, mean, sigma)
        multi_sample.append(sample)
        multi_sample_mean.append(sample_mean)
    return np.array(multi_sample), np.array(multi_sample_mean)


def standard_Riccati_iteration(A, B, P, Q, R):
    return Q + matmul3(np.transpose(A), P, A) - matmul7(np.transpose(A), P, B, np.linalg.inv(R+matmul3(np.transpose(B), P, B)), np.transpose(B), P, A)


def standard_LQG_control_gain(A, B, P, R):
    return - matmul4(np.linalg.inv(R + matmul3(np.transpose(B), P, B)), np.transpose(B), P, A)


def worst_case_distribution(sample, x, u, A, B, Xi, P, r, lam):
    N = len(sample) # Number of samples
    dim = len(sample[0]) # Dimension of disturbance w
    sample_new = np.zeros((N, dim, 1))
    for i in range(N):
        temp1 = lam*np.eye(dim) - matmul3(np.transpose(Xi), P, Xi)
        temp2 = matmul3(np.transpose(Xi), P, np.matmul(A, x) + np.matmul(B, u))+np.matmul(np.transpose(Xi), r) + lam * np.reshape(sample[i], (dim, 1))
        sample_new[i] = np.linalg.solve(temp1, temp2)
    rand = np.random.randint(N)
    return sample_new[rand]


def minimax_Riccati_iteration(A, B, Xi, Q, R, P, r, z, sample, sample_mean, lam):
    n = len(A)
    k = len(Xi[0])
    W = matmul3(B, np.linalg.inv(R), np.transpose(B)) - 1.0/lam*np.matmul(Xi, np.transpose(Xi))
    temp1 = np.linalg.inv(np.eye(n) + np.matmul(P, W))
    temp2 = matmul3(P, Xi, sample_mean) + r
    temp3 = np.linalg.inv(np.eye(k) - 1.0/lam*matmul3(np.transpose(Xi), P, Xi))
    temp4 = np.linalg.inv(np.eye(n) - 1.0/lam*matmul3(P, Xi, np.transpose(Xi)))
    P_result = Q + matmul4(np.transpose(A), temp1, P, A)
    r_result = matmul3(np.transpose(A), temp1, temp2)
    z_temp1 = np.zeros((1, 1))
    for s in range(len(sample)):
        w = sample[s]
        z_temp1 = z_temp1 + matmul6(np.transpose(w), temp3, np.transpose(Xi), P, Xi, w)
    z_temp1 = z_temp1 / len(sample)
    z_temp2 = matmul6(np.transpose(sample_mean), np.transpose(Xi), temp1 - temp4, P, Xi, sample_mean)
    z_temp3 = matmul3(2*np.matmul(np.transpose(sample_mean), np.transpose(Xi))-np.matmul(np.transpose(r), W), temp1, r)
    z_result = z + z_temp1 + z_temp2 + z_temp3
    return P_result, r_result, z_result


def minimax_LQR_control_gain(A, B, Xi, Q, R, P, r, sample_mean, lam):
    n = len(A)
    temp1 = np.eye(n) + matmul4(P, B, np.linalg.inv(R), np.transpose(B)) - 1.0/lam*matmul3(P, Xi, np.transpose(Xi))
    temp2 = matmul3(P, Xi, sample_mean) + r
    K = - matmul5(np.linalg.inv(R), np.transpose(B), np.linalg.inv(temp1), P, A)
    L = - matmul4(np.linalg.inv(R), np.transpose(B), np.linalg.inv(temp1), temp2)
    return K, L

def objective_function(A, B, Xi, Q, Q_f, R, lam, theta, stage_number, initial_state, sample, sample_mean):
    P = Q_f
    r = np.zeros((len(A), 1))
    z = np.zeros((1, 1))

    if lam < 0:
        return math.inf
    for t in range(stage_number, 0, -1):
        eigen = linalg.eig(matmul3(np.transpose(Xi), P, Xi))
        eigenvalues = eigen[0]

        # Assumption1 Test
        if np.max(eigenvalues.real) > lam:
            return math.inf

        # Riccati
        P, r, z = minimax_Riccati_iteration(A, B, Xi, Q, R, P, r, z, sample[t-1], sample_mean[t-1], lam)

    return lam*theta*theta + (matmul3(np.transpose(initial_state), P, initial_state)[0][0]
                              + 2*np.matmul(np.transpose(r), initial_state)[0][0] + z[0][0])/stage_number
