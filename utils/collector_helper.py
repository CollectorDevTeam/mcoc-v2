'''Helper functions for Collector Bot'''


def tabulate_data(table_data, width=None, align=None, rotate=False, separate_header=True):
    '''Turn a list of lists into a tabular string'''
    print('tabulate_data')
    align_opts = {'center': '^', 'left': '<', 'right': '>'}
    default_align = 'center'
    default_width = 5

    rows = []
    if table_data:
        tbl_cols = len(table_data[0])
        if any(len(x) != tbl_cols for x in table_data):
            raise IndexError('Array is not uniform')

        width = pad_list(width, tbl_cols, default_width)
        align = pad_list(align, tbl_cols, default_align)
        print(width)
        print(align)
        for i in iter_rows(table_data, rotate):

            fstr = '{:{}{}}'.format(i[0], align_opts[align[0]], width[0])
            if tbl_cols > 1:
                for n in range(1, tbl_cols):
                    fstr += '|{:{}{}}'.format(i[n], align_opts[align[n]], width[n])
            rows.append(fstr)
        if separate_header:
            rows.insert(1, '-' * (sum(width) + len(width)))
    return '\n'.join(rows)


def pad_list(lst, new_length, pad_value):
    '''Pad out a list to a desired length'''
    if lst is None:
        lst = []
    pad = [pad_value] * (new_length - len(lst))
    for x in pad:
        lst.append(x)
    return lst


def iter_rows(array, rotate):
    if not rotate:
        for i in array:
            yield i
    else:
        for j in range(len(array[0])):
            row = []
            for i in range(len(array)):
                row.append(array[i][j])
            yield row
