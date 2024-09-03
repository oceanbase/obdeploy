// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/:name/remove': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 78, data: null, msg: '革较共因看七总思干水认和你手性议些。', success: false });
  },
};
