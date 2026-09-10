
from collections.abc import Callable

import numpy as np

# Define a grid (list of list)
Grid = list[list[int]]  # 9x9, 0 = empty cell

MAX_LOOP_ITERATIONS = 10000

# Define each 3x3 cell
Q11 = (slice(0,3),slice(0,3))
Q12 = (slice(0,3),slice(3,6))
Q13 = (slice(0,3),slice(6,9))
Q21 = (slice(3,6),slice(0,3))
Q22 = (slice(3,6),slice(3,6))
Q23 = (slice(3,6),slice(6,9))
Q31 = (slice(6,9),slice(0,3))
Q32 = (slice(6,9),slice(3,6))
Q33 = (slice(6,9),slice(6,9))
Q = [Q11,Q12,Q13,Q21,Q22,Q23,Q31,Q32,Q33]

def decide_Q(r:int,c:int) -> tuple[slice,slice]:
    """Docs"""
    if r<3:
        if c<3:
            return Q11
        elif c>2 and c<6:
            return Q12
        else:
            return Q13
    elif r>2 and r<6:
        if c<3:
            return Q21
        elif c>2 and c<6:
            return Q22
        else:
            return Q23
    else:
        if c<3:
            return Q31
        elif c>2 and c<6:
            return Q32
        else:
            return Q33


def create_box_shapes(i:int,direction:str='horizontal') -> np.ndarray:
    t = np.zeros(3*3,dtype='bool').reshape(3,3)
    if direction=='horizontal':
        t[i,:]=True
    else:
        t[:,i]=True
    return t

# Create dictionary with 3x3 grids with horizontal and vertical boolen stripes
box_check = {i:[create_box_shapes(i,'horizontal'),create_box_shapes(i,'vertical')] for i in range(3)}

# Boolean vectors checking each box position for rows and columns.
check_vector1 = np.zeros(9,dtype='bool')
check_vector1[:3]=True
check_vector2 = np.zeros(9,dtype='bool')
check_vector2[3:6]=True
check_vector3 = np.zeros(9,dtype='bool')
check_vector3[6:]=True

def cleanup_matrix(matrix:np.ndarray) -> np.ndarray:
    rows,cols = np.where(matrix.sum(axis=0)>10)
    for i in range(matrix.shape[0]):
        for r,c in zip(rows,cols):
            r,c = int(r),int(c)
            if matrix[i][r,c]!=10:
                matrix[i][r,c]=0
    return matrix

def resolve_ones(matrix:np.ndarray,binary_mask:np.ndarray) -> np.ndarray:
    rows,cols = np.where(binary_mask)
    for i in range(matrix.shape[0]):
        for r,c in zip(rows,cols):
            r,c = int(r),int(c)
            if matrix[i][r,c] == 1:
                matrix[i][r,:] = 0
                matrix[i][:,c] = 0
                matrix[i][decide_Q(r,c)] = 0
                matrix[i][r,c]=10
    return matrix

def resolve_hidden_singles(matrix:np.ndarray) -> np.ndarray:
    for i in range(matrix.shape[0]):
        layer = matrix[i]
        for r in range(9):
            cs = np.where(layer[r,:]==1)[0]
            if cs.size == 1:
                c = int(cs[0])
                matrix[:,r,c] = 0
                matrix[i][r,:] = 0
                matrix[i][:,c] = 0
                matrix[i][decide_Q(r,c)] = 0
                matrix[i][r,c] = 10
        for c in range(9):
            rs = np.where(layer[:,c]==1)[0]
            if rs.size == 1:
                r = int(rs[0])
                matrix[:,r,c] = 0
                matrix[i][r,:] = 0
                matrix[i][:,c] = 0
                matrix[i][decide_Q(r,c)] = 0
                matrix[i][r,c] = 10
        for q in Q:
            rr,cc = np.where(layer[q]==1)
            if rr.size == 1:
                r,c = q[0].start+int(rr[0]), q[1].start+int(cc[0])
                matrix[:,r,c] = 0
                matrix[i][r,:] = 0
                matrix[i][:,c] = 0
                matrix[i][decide_Q(r,c)] = 0
                matrix[i][r,c] = 10
    return matrix

def resolving_pointing_numbers(matrix:np.ndarray) -> np.ndarray:
    for i in range(matrix.shape[0]):
        layer = matrix[i]
        for q in Q:
            box_mask = layer[q]==1
            box_mask_sum = np.sum(box_mask)
            if box_mask_sum in (2,3):
                for rc,masks in box_check.items():
                    for j,mask in enumerate(masks):
                        overlap = np.sum(box_mask & mask)
                        if (box_mask_sum==2 and overlap==2) or (box_mask_sum==3 and overlap==3):
                            coords = np.array(np.where(box_mask)).T+np.array([q[0].start,q[1].start])
                            if j==0:
                                matrix[i][rc+q[0].start,:] = 0
                            else:
                                matrix[i][:,rc+q[1].start] = 0
                            matrix[i][coords[:,0],coords[:,1]] = 1
    return matrix

def clean_box(matrix:np.ndarray,index:int,Q:tuple[slice,slice],fill_boolean:np.ndarray,row:bool=True) -> np.ndarray:
    matrix[Q]=0
    if row:
        matrix[index,fill_boolean]=1
    else:
        matrix[fill_boolean,index]=1
    return matrix

def resolving_claiming_boxes(matrix:np.ndarray) -> np.ndarray:
    for i in range(matrix.shape[0]):
        layer = matrix[i]
        for r in range(9):
            row_ones = layer[r,:]==1
            row_ones_sum = row_ones.sum()
            if row_ones_sum in [2,3]:
                if (np.sum(row_ones & check_vector1)==2 and row_ones_sum==2) or (np.sum(row_ones & check_vector1)==3 and row_ones_sum==3):
                    layer = clean_box(layer,r,decide_Q(r,0),row_ones & check_vector1)
                elif (np.sum(row_ones & check_vector2)==2 and row_ones_sum==2) or (np.sum(row_ones & check_vector2)==3 and row_ones_sum==3):
                    layer = clean_box(layer,r,decide_Q(r,3),row_ones & check_vector2)
                elif (np.sum(row_ones & check_vector3)==2 and row_ones_sum==2) or (np.sum(row_ones & check_vector3)==3 and row_ones_sum==3):
                    layer = clean_box(layer,r,decide_Q(r,6),row_ones & check_vector3)
        for c in range(9):
            col_ones = layer[:,c]==1
            col_ones_sum = col_ones.sum()
            if col_ones_sum in [2,3]:
                if (np.sum(col_ones & check_vector1)==2 and col_ones_sum==2) or (np.sum(col_ones & check_vector1)==3 and col_ones_sum==3):
                    layer = clean_box(layer,c,decide_Q(0,c),col_ones & check_vector1,row=False)
                elif (np.sum(col_ones & check_vector2)==2 and col_ones_sum==2) or (np.sum(col_ones & check_vector2)==3 and col_ones_sum==3):
                    layer = clean_box(layer,c,decide_Q(3,c),col_ones & check_vector2,row=False)
                elif (np.sum(col_ones & check_vector3)==2 and col_ones_sum==2) or (np.sum(col_ones & check_vector3)==3 and col_ones_sum==3):
                    layer = clean_box(layer,c,decide_Q(6,c),col_ones & check_vector3,row=False)
    return matrix 

def is_sudoku_solved(matrix:np.ndarray) -> bool:
    solved_sudoku = np.argmax(matrix,axis=0)+1
    sub_square_check = np.all([np.unique(solved_sudoku[q]).shape[0]==9 for q in Q])
    vertical_check = np.all([np.unique(solved_sudoku[i,:]).shape[0]==9 for i in range(solved_sudoku.shape[0])])
    horizontal_check = np.all([np.unique(solved_sudoku[:,i]).shape[0]==9 for i in range(solved_sudoku.shape[0])])
    if np.all([sub_square_check,vertical_check,horizontal_check]):
        print('Sudoku solved')
        return True
    else:
        return False

def solving_loop(matrix:np.ndarray) -> tuple[str,np.ndarray]:
    continue_loop = True
    matrix = cleanup_matrix(matrix)
    remaining_ones = np.sum(matrix==1)
    loop_counter = 0
    while continue_loop:
        z_sum = np.sum(matrix,axis=0)
        z_sum_binary = z_sum == 1
        if np.any(z_sum_binary):
            matrix = resolve_ones(matrix,z_sum_binary)
        else:
            matrix = resolve_hidden_singles(matrix)
            matrix = resolving_pointing_numbers(matrix)
            matrix = resolving_claiming_boxes(matrix)
        decision_check = np.sum(matrix==1)
        if np.any(matrix.sum(axis=0)==0):
            return 'dead end',matrix
        if decision_check==remaining_ones:
            return 'decision',matrix
        if np.all(matrix.sum(axis=0)==10) and is_sudoku_solved(matrix):
            return 'solved',matrix
        remaining_ones = decision_check
        if loop_counter > MAX_LOOP_ITERATIONS:
            break
        loop_counter += 1
    return 'max iterations',matrix

def recursive_solve(status:str,matrix:np.ndarray,depth:int) -> tuple[str,np.ndarray,int]:
    if status == 'solved':
        return status,matrix,depth
    depth += 1
    rows,cols = np.where(matrix.sum(axis=0)==2)
    if rows.size==0:
        rows,cols = np.where(matrix.sum(axis=0)>2)
    for r,c in zip(rows,cols):
        r,c = int(r),int(c)
        z_index = np.where(matrix[:,r,c]==1)[0]
        for z in z_index:
            new_matrix = matrix.copy()
            new_matrix[:,r,c] = 0
            new_matrix[z][r,:] = 0
            new_matrix[z][:,c] = 0
            new_matrix[z][decide_Q(r,c)] = 0
            new_matrix[z][r,c] = 10
            new_status,new_matrix = solving_loop(new_matrix)
            if new_status=='max iterations':
                new_status,new_matrix = solving_loop(new_matrix)
            if new_status == 'solved':
                return new_status,new_matrix,depth
            elif new_status == 'decision':
                results_status,results_matrix,depth = recursive_solve(new_status,new_matrix,depth)
                if results_status == 'solved':
                    return results_status,results_matrix,depth
            else:
                continue
    return 'dead end',matrix,depth-1


def grid_to_coordinate_lists(grid: Grid) -> tuple[list[int], list[int], list[int]]:
    """Parallel (rows, cols, values) — one entry per filled cell."""
    rows, cols, values = [], [], []
    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v:
                rows.append(r)
                cols.append(c)
                values.append(v)
    return rows, cols, values

def matrix_to_grid(solved_sudoku: np.ndarray) -> Grid:
    """Docs"""
    solved_sudoku = np.argmax(solved_sudoku,axis=0)+1
    grid = [[0] * 9 for _ in range(9)]
    for r in range(9):
        for c in range(9):
            grid[r][c] = solved_sudoku[r,c].item()
    return grid

def solve(grid: Grid, progress_callback: Callable[[str], None] | None = None) -> tuple[str, Grid]:
    """Solve a 9x9 sudoku. Called by the GUI's Solve button.

    Args:
        grid: 9x9 grid of ints, 0 for empty cells. Already checked by the GUI
            to contain no row/column/box conflicts.
        progress_callback: optional callback for short human-readable status
            updates (e.g. "trying 4 at (2,5)") shown live in the GUI. May be
            called from a background thread; safe to ignore or call often.

    Returns:
        (status, result_grid): status is "solved" or "unsolvable".
        result_grid is the completed grid on "solved", or a best-effort
        (possibly partial) grid otherwise.
    """
    rows,cols,values = grid_to_coordinate_lists(grid)

    sudoku_matrix = np.ones((9,9,9),dtype='int8')

    for r,c,v in zip(rows,cols,values):
        layer = v-1
        sudoku_matrix[layer][decide_Q(r,c)] = 0
        sudoku_matrix[layer,r,:] = 0
        sudoku_matrix[layer,:,c] = 0
        sudoku_matrix[layer,r,c] = 10

    status,sudoku_matrix = solving_loop(sudoku_matrix)

    if status == 'max iterations':
        status,sudoku_matrix = solving_loop(sudoku_matrix)

    if status=='solved':
        return status,matrix_to_grid(sudoku_matrix)
    else:
        status,sudoku_matrix,_ = recursive_solve(status,sudoku_matrix,0)
        if status=='solved':
            return status,matrix_to_grid(sudoku_matrix)
        else:
            return 'currently unsolvable',matrix_to_grid(sudoku_matrix)
        
