import pandas as pd


### out-of-sample test types = fixed, sliding, and rolling
def is_oos_data(data, type = 'sliding', n_lookback = 0, n_sliding = 0):
    n_total = len(data)

    data_is = []
    data_oos = []

    ## type = 1: single train set defined by n_lookback, single test set from n_lookback:n_total
    if type == 'fixed':
        data_is.append(data[:n_lookback - 1])
        data_oos.append(data[n_lookback::])
    elif type == 'rolling':
        k = n_lookback
        while k < n_total-1:
            data_is.append(data[(k-n_lookback):(k - 1)])
            k2 = k + n_sliding - 1 if (k+n_sliding) <= n_total else n_total - 1
            data_oos.append(data[k:k2])
            k = k2
    elif type == 'sliding':
        k = n_lookback
        while k < n_total-1:
            data_is.append(data[:k - 1])
            k2 = k + n_sliding - 1 if (k+n_sliding) <= n_total else n_total - 1
            data_oos.append(data[k:k2])
            k = k2
    return data_is, data_oos