from fastapi import HTTPException, status



def create_400(msg:str)->HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=msg)




def create_404(msg:str)->HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=msg)

def create_401(msg:str)->HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail=msg)


def create_403(msg:str)->HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=msg)


def create_409(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

def create_500(msg:str)->HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=msg)
