// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/install': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 88, data: null, msg: '则第这及群利听构电月局基济。', success: true });
  },
};
