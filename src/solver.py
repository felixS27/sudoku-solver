
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
    """Find the 3x3 box that a grid cell belongs to.

    Args:
        r: Row index of the cell (0-8).
        c: Column index of the cell (0-8).

    Returns:
        The (row_slice, col_slice) pair, one of Q11..Q33, that selects the
        3x3 box containing (r, c).
    """
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
    """Build a 3x3 boolean mask marking one row or column of a box.

    Used to precompute box_check, which is later used to test whether a
    box's remaining candidates for a digit all line up in a single row or
    column (see resolving_pointing_numbers).

    Args:
        i: Index (0-2) of the row or column to mark True within the 3x3 box.
        direction: 'horizontal' marks row i, anything else marks column i.

    Returns:
        A 3x3 boolean array with row/column i set to True and the rest False.
    """
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
    """Clear leftover candidates in cells that already hold a solved digit.

    A solved cell has value 10 on its solved digit's layer; if other layers
    at that cell still hold stray 1 candidates, the per-cell sum across
    layers exceeds 10. This zeroes out every layer except the solved one
    for such cells.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.

    Returns:
        The same matrix, with stray candidates removed from solved cells.
    """
    rows,cols = np.where(matrix.sum(axis=0)>10)
    for i in range(matrix.shape[0]):
        for r,c in zip(rows,cols):
            r,c = int(r),int(c)
            if matrix[i][r,c]!=10:
                matrix[i][r,c]=0
    return matrix

def resolve_ones(matrix:np.ndarray,binary_mask:np.ndarray) -> np.ndarray:
    """Apply the naked-singles technique to cells with exactly one candidate.

    For each flagged cell, finds the one digit layer still holding a 1
    (its only remaining candidate), marks it solved (10) there, and
    eliminates that digit from the rest of the cell's row, column and box.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.
        binary_mask: 9x9 boolean array, True at cells whose candidate count
            (summed across digit layers) is exactly 1.

    Returns:
        The same matrix, with naked singles resolved and their digit
        eliminated from peer cells.
    """
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
    """Apply the hidden-singles technique to every digit layer.

    For each digit layer, checks every row, column and box; if only one
    cell in that unit can still hold the digit, marks it solved (10) there
    and eliminates the digit from the rest of the cell's row, column and
    box.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.

    Returns:
        The same matrix, with hidden singles resolved.
    """
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
    """Apply the pointing pairs/triples technique to every digit layer.

    For each box, if the digit's 2 or 3 remaining candidates within the box
    all line up in a single row or column, the digit is eliminated as a
    candidate from the rest of that row or column outside the box.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.

    Returns:
        The same matrix, with pointing pairs/triples eliminations applied.
    """
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
    """Restrict one digit layer's candidates within a box to a single row/column.

    Clears every candidate in the given box, then restores candidates only
    at the positions flagged in fill_boolean along the given row (or
    column) index. Used by resolving_claiming_boxes to remove a digit's
    candidates from the rest of a box once its remaining candidates in a
    row/column are known to all fall inside that box.

    Args:
        matrix: One digit layer (9x9) of the candidate matrix, modified
            in place.
        index: Row index (if row=True) or column index (if row=False) to
            restore candidates on.
        Q: (row_slice, col_slice) selecting the box to clear.
        fill_boolean: 1D boolean array (length 9) marking which columns
            (if row=True) or rows (if row=False) to restore as candidates.
        row: If True, index/fill_boolean address a row; otherwise a column.

    Returns:
        The same layer, with the box cleared except for the restored
        row/column positions.
    """
    matrix[Q]=0
    if row:
        matrix[index,fill_boolean]=1
    else:
        matrix[fill_boolean,index]=1
    return matrix

def resolving_claiming_boxes(matrix:np.ndarray) -> np.ndarray:
    """Apply the claiming (box-line reduction) technique to every digit layer.

    For each row and column, if the digit's 2 or 3 remaining candidates all
    fall within a single box, the digit is eliminated as a candidate from
    the rest of that box.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.

    Returns:
        The same matrix, with claiming/box-line eliminations applied.
    """
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
    """Check whether the candidate matrix represents a fully, validly solved sudoku.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col). Each cell's
            digit is taken as the layer with the highest value (the solved
            layer holds 10), so this assumes every cell already has a
            single dominant layer.

    Returns:
        True if every row, column and box contains each digit 1-9 exactly
        once; False otherwise.
    """
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
    """Repeatedly apply logical solving techniques until progress stalls.

    Alternates naked singles with hidden singles, pointing pairs/triples
    and claiming boxes, looping until the puzzle is solved, hits a dead
    end (some cell has no remaining candidates), stops making progress
    (a guess is needed), or exceeds MAX_LOOP_ITERATIONS.

    Args:
        matrix: 9x9x9 candidate matrix (digit layer, row, col), modified
            in place.

    Returns:
        A (status, matrix) tuple. status is one of:
            'solved': the puzzle is fully and validly solved.
            'dead end': some cell has no remaining candidates.
            'decision': no further logical progress was made; a guess
                (see recursive_solve) is required to continue.
            'max iterations': MAX_LOOP_ITERATIONS was reached without
                solving or stalling.
    """
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
    """Backtracking search used when solving_loop stalls on a 'decision'.

    Picks a cell with the fewest remaining candidates (preferring 2, then
    falling back to more), tries each candidate digit in turn by guessing
    it and re-running solving_loop, and recurses whenever a guess again
    stalls at 'decision'. Returns as soon as a branch solves the puzzle;
    otherwise backtracks and tries the next candidate/cell.

    Args:
        status: Status from the caller's last solving_loop call (e.g.
            'decision'); used only to short-circuit if already 'solved'.
        matrix: 9x9x9 candidate matrix (digit layer, row, col) at the point
            where logical solving stalled.
        depth: Current recursion depth, for tracking how many guesses were
            made.

    Returns:
        A (status, matrix, depth) tuple. status is 'solved' if a solution
        was found, otherwise 'dead end' if every branch failed.
    """
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
    """Extract the filled cells of a grid as parallel coordinate lists.

    Args:
        grid: 9x9 grid of ints, 0 for empty cells.

    Returns:
        (rows, cols, values): three equal-length lists, one entry per
        filled cell, giving its row index, column index and digit (1-9).
    """
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
    """Convert a candidate matrix into a plain 9x9 grid of digits.

    Args:
        solved_sudoku: 9x9x9 candidate matrix (digit layer, row, col). Each
            cell's digit is taken as the layer with the highest value (the
            solved layer holds 10), so this assumes every cell already has
            a single dominant layer.

    Returns:
        9x9 grid of ints (1-9) with the digit read off from each cell.
    """
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
        
